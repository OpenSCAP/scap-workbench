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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_BASE_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_BASE_H_

#include "ForwardDecls.h"

#include "Scanner.h"
#include "OscapCapabilities.h"

#include <QStringList>
#include <QProcess>

class OscapScannerBase : public Scanner
{
    Q_OBJECT

    public:
        OscapScannerBase();
        virtual ~OscapScannerBase();

        virtual void cancel();

        virtual void getResults(QByteArray& destination);
        virtual void getReport(QByteArray& destination);
        virtual void getARF(QByteArray& destination);

    protected:
        virtual void signalCompletion(bool canceled);

        bool checkPrerequisites();
        QString surroundQuote(const QString& input)const;
        QStringList buildEvaluationArgs(const QString& inputFile,
                                        const QString& tailoringFile,
                                        const QString& resultFile,
                                        const QString& reportFile,
                                        const QString& arfFile,
                                        bool onlineRemediation,
                                        bool ignoreCapabilities = false) const;
        QStringList buildOfflineRemediationArgs(const QString& resultInputFile,
                                                const QString& resultFile,
                                                const QString& reportFile,
                                                const QString& arfFile,
                                                bool ignoreCapabilities = false) const;

        /// Last read rule id
        QString mLastRuleID;
        /// Last downloading file
        QString mLastDownloadingFile;

        enum ReadingState
        {
            RS_READING_PREFIX,
            RS_READING_RULE_RESULT,
            RS_READING_DOWNLOAD_FILE,
            RS_READING_DOWNLOAD_FILE_STATUS
        };

        ReadingState mReadingState;

        /// We keep filling this buffer until we reach : or \n
        QString mReadBuffer;

        /**
         * @brief Tries to read something (at least one character) from stdout
         *
         * @note ReadChannel must be set properly before calling this method!
         * @returns false when there is nothing to be read, true otherwise
         * @see readStdOut
         */
        bool tryToReadStdOutChar(QProcess& process);

        /**
         * @brief Reads as much as possible from stdout of given process
         */
        void readStdOut(QProcess& process);
        void watchStdErr(QProcess& process);

        /**
         * @brief Converts OpenSCAP CLI messages to SCAP Workbench GUI messages.
         */
        QString guiFriendlyMessage(const QString& cliMessage);

        bool mCancelRequested;

        OscapCapabilities mCapabilities;

        QByteArray mResults;
        QByteArray mReport;
        QByteArray mARF;
};

#endif
