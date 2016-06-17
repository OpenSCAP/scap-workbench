/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#ifndef SCAP_WORKBENCH_SCANNER_H_
#define SCAP_WORKBENCH_SCANNER_H_

#include "ForwardDecls.h"

#include <QObject>
#include <QByteArray>

extern "C"
{
#include <xccdf_benchmark.h>
}

enum ScannerMode
{
    SM_SCAN,
    SM_SCAN_ONLINE_REMEDIATION,
    SM_OFFLINE_REMEDIATION
};

/**
 * @brief The scanner interface class
 *
 * Classes implementing this interface are responsible for actually scanning
 * and remediating the targets they are given.
 *
 * In essence we pass session data and target and expect to get the 3 resulting
 * files when scanning or remediation finishes. Results for scans and remediations
 * are of the same type so there is only one interface class. Furthermore, there
 * is a mode where the scanner scans and remediates at the same time which is
 * also in favor of a single interface for this.
 *
 * All implementors of the interface have to keep in mind that scanning might
 * (and actually always does at the moment) run in parallel to the main event
 * loop. You are advised to do all communication between threads using Qt's
 * signal & slot system.
 */
class Scanner : public QObject
{
    Q_OBJECT

    public:
        /**
         * @param thread Thread that runs the evaluation
         * @param session Session with all the settings required for scanning
         * @param target Representation of the target machine to scan
         */
        Scanner();

        virtual ~Scanner();

        virtual void setScanThread(QThread* thread);
        virtual void setMainThread(QThread* thread);
        virtual void setDryRun(bool dryRun);
        virtual void setSkipValid(bool skip);
        bool getSkipValid() const;
        virtual void setFetchRemoteResources(bool fetch);
        bool getFetchRemoteResources() const;
        virtual void setSession(ScanningSession* session);
        ScanningSession* getSession() const;
        virtual void setTarget(const QString& target);
        const QString& getTarget() const;

        virtual void setScannerMode(ScannerMode mode);
        ScannerMode getScannerMode() const;

        /**
         * @brief Retrieves XCCDF results from the scan
         *
         * @param destination QByteArray that will be filled with XCCDF result
         * @note This will only work after "evaluate()" finished successfully.
         */
        virtual void getResults(QByteArray& destination) = 0;

        /**
         * @brief Retrieves HTML report from the scan
         *
         * @param destination QByteArray that will be filled with HTML report
         * @note This will only work after "evaluate()" finished successfully.
         */
        virtual void getReport(QByteArray& destination) = 0;

        /**
         * @brief Retrieves results in Result DataStream (ARF) format
         *
         * @param destination QByteArray that will be filled with ARF results
         * @note This will only work after "evaluate()" finished successfully.
         */
        virtual void getARF(QByteArray& destination) = 0;

        virtual void setARFForRemediation(const QByteArray& results);
        const QByteArray& getARFForRemediation() const;

        virtual QStringList getCommandLineArgs() const = 0;

    public slots:
        /**
         * @brief Evaluate with given parameters
         *
         * Probably the most important method of this interface, this will start
         * the evaluation.
         *
         * This method will not return until after evaluation has finished.
         * It will, however, pump the event queue while evaluation is running,
         * so signals, slots and events get delivered and acted upon.
         *
         * You are advised to run evaluate in a separate thread to avoid blocking
         * the GUI's main loop.
         */
        virtual void evaluate() = 0;

        /**
         * @brief A thin wrapper around evaluate that catches all exceptions
         *
         * Exceptions are "converted" into error notifications and passed along
         * accordingly. The main reason for this method is to avoid throwing
         * exception in the Qt event loop.
         */
        void evaluateExceptionGuard();

        /**
         * @brief Requests to cancel the evaluation
         *
         * Usually fired via a signal from another thread, this will make sure
         * that evaluation is canceled "as soon as possible". Do not count on it
         * being canceled immediately when this method returns!
         */
        virtual void cancel() = 0;

    signals:
        /**
         * Main window hooks into this signal to receive feedback about evaluation
         * progress. Some of the data returned may be misleading, skewed or downright
         * false! You should use the resulting XCCDF report or ARF results for
         * conclusive results instead of data returned via this signal.
         */
        void progressReport(const QString& rule_id, const QString& result);

        /**
         * @brief Scanner signals this when it wants to give high-level progress
         */
        void infoMessage(const QString& message);

        /**
         * @brief Scanner signals this when non-critical issues happen
         *
         * Scanning may or may not continue after this is emitted.
         */
        void warningMessage(const QString& message);

        /**
         * @brief Scanner signals this when critical and/or important issues happen
         *
         * Scanning may or may not continue after this is emitted.
         */
        void errorMessage(const QString& message);

        /**
         * Signaled when evaluation finishes after cancel was requested.
         */
        void canceled();

        /**
         * Signaled when evaluation finishes without any critical issues and
         * without any cancel requests.
         */
        void finished();

    protected:
        /// Which mode should the scanner run in for the next evaluation() invocation
        ScannerMode mScannerMode;

        /// Thread that is running the evaluation
        QThread* mScanThread;
        /// Thread that is running the main window event queue
        QThread* mMainThread;

        /// If true no evaluation will take place
        bool mDryRun;

        /// If true openscap will skip validation when interpreting the content
        bool mSkipValid;

        /// If true openscap will download of remote OVAL content referenced from XCCDF
        bool mFetchRemoteResources;

        /// Session containing setup parameters for the scan
        ScanningSession* mSession;
        /// Target machine we should be scanning
        QString mTarget;

        /// Stores results that will be used in case scanner mode is SM_OFFLINE_REMEDIATION
        QByteArray mARFForRemediation;

        /**
         * A helper method that will signal completion and finish off the thread.
         */
        virtual void signalCompletion(bool canceled);
};

#endif
