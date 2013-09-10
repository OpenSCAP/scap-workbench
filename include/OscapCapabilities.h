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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_CAPABILITIES_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_CAPABILITIES_H_

#include "ForwardDecls.h"

#include <QString>

/**
 * @brief Figures out oscap capabilities based on version and compile flags
 */
class OscapCapabilities
{
    public:
        OscapCapabilities();

        /**
         * @brief Resets all stored capabilities to unknown or not supported
         *
         * @see OscapCapabilities::parse
         */
        void clear();

        /**
         * @brief Parses output of 'oscap --v' and interprets the results
         *
         * The results are stored in this class. All previously stored results
         * will be lost!
         *
         * @param mmv Verbatim output of 'oscap --v' to be processed
         */
        void parse(const QString& mmv);

        /**
         * @brief Returns version of openscap that was detected
         */
        const QString& getOpenSCAPVersion() const;

        /**
         * @brief Returns true if enough is supported for workbench to use the oscap
         *
         * This is a critical requirement, for very old oscap versions this will
         * return false and these versions just can't be used with the new
         * workbench!
         */
        bool baselineSupport() const;

        /**
         * @brief Returns true if --progress flag is supported
         *
         * If the flag is not supported, we don't do any GUI progress reporting.
         */
        bool progressReporting() const;

        /**
         * @brief Returns true of online remediation is supported
         *
         * Only returns true if --progress flag is supported and works correctly for online remediation
         * If the flag is not supported, we don't do any GUI progress reporting when remediating.
         */
        bool onlineRemediation() const;

        /**
         * @brief Returns true if source datastreams are supported
         */
        bool sourceDatastreams() const;

        /**
         * @brief Returns true if ARFs are supported as input
         */
        bool ARFInput() const;

        /**
         * @brief Returns true if tailoring is supported to the full extent workbench requires
         *
         * This means that XCCDF 1.1 can take tailoring via the openscap extension and XCCDF 1.2
         * has proper tailoring including profile inheritance.
         */
        bool tailoringSupport() const;

        const QString& XCCDFVersion() const;
        const QString& OVALVersion() const;
        const QString& CPEVersion() const;

    private:
        QString mVersion;

        bool mBaselineSupport;
        bool mProgressReporting;
        bool mOnlineRemediation;
        bool mSourceDataStreams;
        bool mARFInput;
        bool mTailoringSupport;
        bool mSCE;

        QString mXCCDFVersion;
        QString mOVALVersion;
        QString mCPEVersion;
        QString mSCEVersion;
};

#endif
